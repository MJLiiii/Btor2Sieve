(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x272 ((_ extract 2 1) i_4)))
 (let ((?x437 ((_ extract 0 0) i_4)))
 (let ((?x46 (concat ?x437 ?x272)))
 (let ((?x1722 (bvor (bvshl i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
 (let ((?x318 (ite (and (distinct ?x1722 ?x46) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x318 (_ bv1 1)))))))))
(assert
 (let (($x212 (= i_4 (_ bv0 3))))
(not $x212)))
(check-sat)
