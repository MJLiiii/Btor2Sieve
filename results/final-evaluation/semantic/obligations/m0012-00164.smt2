(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x44 ((_ extract 2 1) i_4)))
 (let ((?x7064 ((_ extract 0 0) i_4)))
 (let ((?x517 (concat ?x7064 ?x44)))
 (let ((?x3118 (bvor (bvshl i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
 (let ((?x2814 (ite (and (distinct ?x3118 ?x517) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x2814 (_ bv1 1)))))))))
(assert
 (let ((?x44 ((_ extract 2 1) i_4)))
(let (($x5390 (bvuge ?x44 (_ bv1 2))))
(not $x5390))))
(check-sat)
