(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1190 (bvule s_7 (_ bv128 8))))
(not $x1190)))
(check-sat)
