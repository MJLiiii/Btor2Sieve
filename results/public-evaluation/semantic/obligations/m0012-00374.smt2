(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_40 () (_ BitVec 70))
(assert
 (let ((?x209 ((_ extract 69 54) i_40)))
 (let ((?x2762 ((_ extract 53 0) i_40)))
 (let ((?x1012 (concat ?x2762 ?x209)))
 (let ((?x2249 (bvor (bvshl i_40 (bvurem (_ bv18446744073709551616 70) (_ bv70 70))) (bvlshr i_40 (bvsub (_ bv70 70) (bvurem (_ bv18446744073709551616 70) (_ bv70 70)))))))
 (let ((?x1656 (ite (and (distinct ?x2249 ?x1012) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x1656 (_ bv1 1)))))))))
(assert
 (let ((?x2762 ((_ extract 53 0) i_40)))
(let (($x751 (bvuge ?x2762 (_ bv1 54))))
(not $x751))))
(check-sat)
