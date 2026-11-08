(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x324 ((_ extract 2 1) i_4)))
 (let ((?x68 ((_ extract 0 0) i_4)))
 (let ((?x1388 (concat ?x68 ?x324)))
 (let ((?x583 (bvor (bvshl i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
 (let ((?x361 (ite (and (distinct ?x583 ?x1388) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x361 (_ bv1 1)))))))))
(assert
 (let ((?x324 ((_ extract 2 1) i_4)))
(let (($x262 (and (distinct ?x324 (_ bv3 2)) true)))
(not $x262))))
(check-sat)
