(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 (let ((?x3313 ((_ extract 2 1) i_4)))
 (let ((?x265 ((_ extract 0 0) i_4)))
 (let ((?x2501 (concat ?x265 ?x3313)))
 (let ((?x462 (bvor (bvshl i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
 (let ((?x5024 (ite (and (distinct ?x462 ?x2501) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x5024 (_ bv1 1)))))))))
(assert
 (let ((?x462 (bvor (bvshl i_4 (bvurem (_ bv2 3) (_ bv3 3))) (bvlshr i_4 (bvsub (_ bv3 3) (bvurem (_ bv2 3) (_ bv3 3)))))))
(let (($x3420 (= ?x462 (_ bv7 3))))
(not $x3420))))
(check-sat)
